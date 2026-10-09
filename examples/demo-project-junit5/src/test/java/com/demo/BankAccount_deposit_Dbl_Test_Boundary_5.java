package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class BankAccount_deposit_Dbl_Test_Boundary_5 {

    @Test
    public void testDepositWithZeroAmount() {
        BankAccount account = new BankAccount("owner", 100.0);
        try {
            account.deposit(0.0);
            Assertions.fail("Expected IllegalArgumentException was not thrown");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }

}
