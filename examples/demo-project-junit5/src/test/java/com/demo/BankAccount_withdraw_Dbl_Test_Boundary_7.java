package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertThrows;

public class BankAccount_withdraw_Dbl_Test_Boundary_7 {


    @Test
    public void testWithdrawWithZeroAmount() {
        BankAccount account = new BankAccount("John Doe", 100.0);
        assertThrows(IllegalArgumentException.class, () -> account.withdraw(0.0));
    }

}
