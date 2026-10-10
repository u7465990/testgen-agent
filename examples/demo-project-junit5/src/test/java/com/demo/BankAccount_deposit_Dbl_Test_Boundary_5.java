package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class BankAccount_deposit_Dbl_Test_Boundary_5 {


    @Test
    public void testDepositWithZeroAmountThrowsIllegalArgumentException() {
        BankAccount account = new BankAccount("owner", 100.0);

        Assertions.assertThrows(IllegalArgumentException.class, () -> {
            account.deposit(0.0);
        });
    }

}
