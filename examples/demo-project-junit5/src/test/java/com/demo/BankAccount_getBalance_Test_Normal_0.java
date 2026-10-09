package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class BankAccount_getBalance_Test_Normal_0 {


    @Test
    public void testGetBalanceReturnsConstructorInitialBalance() {
        BankAccount account = new BankAccount("Alice", 1000.50);
        double actual = account.getBalance();
        assertEquals(1000.50, actual, 0.0);
    }

}
